from django.shortcuts import render,redirect
from django.urls import reverse

from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import text
from openpyxl import Workbook

from ghost.queries import (
    get_query_estoque_armazens_somados, get_query_produzidos_da_data
)
from ghost.utils.funcs import get_engine
from ghost.views.estruturas import forma_string_codigos, explode_estrutura

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

    wb = Workbook()
    ws = wb.active
    ws.title = "Simulador"

    ws.append([
        "Código Original","Descrição Original","Tipo Orig",
        "Código Pai","Descrição Pai","Tipo Pai",
        "Insumo","Descrição Insumo","Tipo Ins.",
        "Saldo Atual",
        "Saldo Antes","Demanda","Saldo Depois"
    ])

    for i in range(len(codigos)):
        if not codigos[i] or not quantidades[i]:
            codigos.pop(i)
            quantidades.pop(i)
            datas.pop(i)
        else:
            codigos[i] = str(codigos[i]).upper().strip()
            quantidades[i] = int(quantidades[i])
            datas[i] = datetime.strptime(datas[i],"%Y-%m-%d")
            
    demandas = pd.DataFrame({
        "codigos": list(codigos),
        "quant": list(quantidades),
        "datas": list(datas)
    })
    
    engine = get_engine()

    if desconta_prod:
        demandas = desconta_producao_do_mes_atual(demandas, engine)
    
    # ESTOQUE
    query_estoque = get_query_estoque_armazens_somados()
    estoque = pd.read_sql(text(query_estoque), engine, params={
        "codigos": None,
        "armazens": "11,14,17,20"
    })
    
    for dem_i, dem_row in demandas.iterrows():
        codigo = dem_row["codigos"]
        demanda = dem_row["quant"]
        data = dem_row["datas"]

        if demanda == 0: continue

        estrutura, todos_os_codigos = explode_estrutura(
            codigo=codigo,
            data_referencia=data,
            engine=engine,
            abre_todos_os_PIs=False,
            solicitante="lista_de_falta"
        )
        estrutura["quant_utilizada"] = estrutura["quant_utilizada"] * demanda

        for estru_i, estru_row in estrutura.iterrows():

            insumo = estru_row["insumo"]


        # 



    context = {
        "caller": "lista_de_falta_post"
    }
    return render(request, "ghost/listadefalta/listadefalta_tabela.html", context)

def desconta_producao_do_mes_atual(demandas:pd.DataFrame, engine):
    
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
    produzidos_cod_list = list(produzidos["codigo"])

    for i, row in demandas.iterrows():
        data = row["datas"]
        codigo = row["codigos"]
        quant = row["quant"]
        if data.month == mes_atual and data.year == ano_atual and codigo in produzidos_cod_list:
            demandas.at[i,"quant"] = demandas.at[i,"quant"] - produzidos.loc[produzidos["codigo"] == codigo,"quant"].iloc[0]
            if demandas.at[i,"quant"] < 0:
                nova_quant = -demandas.at[i,"quant"]
                demandas.at[i,"quant"] = 0
                produzidos.loc[produzidos["codigo"] == codigo,"quant"] = nova_quant

    return demandas