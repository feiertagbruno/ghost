from django.shortcuts import render,redirect
from django.urls import reverse
from datetime import datetime

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

    lista_de_falta = []

    for i in range(len(codigos)):
        if codigos[i] and quantidades[i]:
            lista_de_falta.append([
                str(codigos[i]).strip().upper(),
                int(quantidades[i]),
                datetime.strptime(f"{datas[i]}-01","%Y-%m-%d")
            ])

    context = {
        "caller": "lista_de_falta_post"
    }
    return render(request, "ghost/listadefalta/listadefalta.html", context)